"""Tests for cronwatch.budget and cronwatch.budget_watcher."""
import pytest
from unittest.mock import MagicMock

from cronwatch.budget import BudgetOptions, BudgetResult, check_budget
from cronwatch.budget_watcher import BudgetWatchOptions, watch_budget, format_budget_notice


# ---------------------------------------------------------------------------
# BudgetOptions.from_dict
# ---------------------------------------------------------------------------

class TestBudgetOptionsFromDict:
    def test_defaults(self):
        opts = BudgetOptions.from_dict({})
        assert opts.enabled is False
        assert opts.max_seconds == 60.0
        assert opts.warn_at_seconds is None

    def test_full(self):
        opts = BudgetOptions.from_dict(
            {"enabled": True, "max_seconds": 30.0, "warn_at_seconds": 20.0}
        )
        assert opts.enabled is True
        assert opts.max_seconds == 30.0
        assert opts.warn_at_seconds == 20.0

    def test_enabled_coerced(self):
        opts = BudgetOptions.from_dict({"enabled": 1})
        assert opts.enabled is True


# ---------------------------------------------------------------------------
# check_budget
# ---------------------------------------------------------------------------

class TestCheckBudget:
    def _opts(self, **kw) -> BudgetOptions:
        return BudgetOptions(enabled=True, max_seconds=100.0, warn_at_seconds=80.0, **kw)

    def test_disabled_always_ok(self):
        opts = BudgetOptions(enabled=False, max_seconds=1.0)
        br = check_budget(999.0, opts)
        assert br.ok()
        assert not br.exceeded
        assert not br.warned

    def test_within_budget(self):
        br = check_budget(50.0, self._opts())
        assert br.ok()
        assert not br.exceeded
        assert not br.warned

    def test_warn_threshold(self):
        br = check_budget(85.0, self._opts())
        assert br.ok()
        assert not br.exceeded
        assert br.warned

    def test_exceeded(self):
        br = check_budget(110.0, self._opts())
        assert not br.ok()
        assert br.exceeded
        assert not br.warned

    def test_no_warn_threshold(self):
        opts = BudgetOptions(enabled=True, max_seconds=100.0, warn_at_seconds=None)
        br = check_budget(85.0, opts)
        assert not br.warned


# ---------------------------------------------------------------------------
# BudgetResult.summary
# ---------------------------------------------------------------------------

def test_summary_disabled():
    br = BudgetResult(False, 5.0, 60.0, None, False, False)
    assert "disabled" in br.summary()


def test_summary_ok():
    br = BudgetResult(True, 5.0, 60.0, None, False, False)
    assert "ok" in br.summary()


def test_summary_exceeded():
    br = BudgetResult(True, 70.0, 60.0, None, True, False)
    assert "exceeded" in br.summary()


# ---------------------------------------------------------------------------
# watch_budget / format_budget_notice
# ---------------------------------------------------------------------------

def _make_result(duration=10.0):
    r = MagicMock()
    r.duration = duration
    return r


def test_watch_budget_disabled_returns_none():
    opts = BudgetWatchOptions(budget=BudgetOptions(enabled=False))
    assert watch_budget(_make_result(), opts) is None


def test_watch_budget_exceeded():
    opts = BudgetWatchOptions(budget=BudgetOptions(enabled=True, max_seconds=5.0))
    br = watch_budget(_make_result(duration=10.0), opts)
    assert br is not None
    assert br.exceeded


def test_format_exceeded():
    br = BudgetResult(True, 110.0, 100.0, 80.0, True, False)
    msg = format_budget_notice(br)
    assert "EXCEEDED" in msg


def test_format_warning():
    br = BudgetResult(True, 85.0, 100.0, 80.0, False, True)
    msg = format_budget_notice(br)
    assert "warning" in msg.lower()


def test_format_ok():
    br = BudgetResult(True, 50.0, 100.0, 80.0, False, False)
    msg = format_budget_notice(br)
    assert "ok" in msg.lower()
