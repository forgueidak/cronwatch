"""Tests for cronwatch.escalation and cronwatch.escalation_tracker."""

from __future__ import annotations

import pytest
from pathlib import Path

from cronwatch.escalation import (
    EscalationLevel,
    EscalationOptions,
    EscalationResult,
    check_escalation,
)
from cronwatch.escalation_tracker import (
    load_consecutive_failures,
    save_consecutive_failures,
    reset_consecutive_failures,
    update_consecutive_failures,
)
from cronwatch.runner import JobResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_result(success: bool) -> JobResult:
    return JobResult(
        command="echo hi",
        returncode=0 if success else 1,
        stdout="ok",
        stderr="",
        duration=0.1,
        timed_out=False,
    )


# ---------------------------------------------------------------------------
# EscalationOptions.from_dict
# ---------------------------------------------------------------------------

class TestEscalationOptionsFromDict:
    def test_defaults(self):
        opts = EscalationOptions.from_dict({})
        assert opts.enabled is False
        assert opts.levels == []

    def test_levels_sorted_by_after_failures(self):
        opts = EscalationOptions.from_dict({
            "enabled": True,
            "levels": [
                {"after_failures": 5, "channels": ["email"]},
                {"after_failures": 1, "channels": ["slack"]},
            ],
        })
        assert [lv.after_failures for lv in opts.levels] == [1, 5]


# ---------------------------------------------------------------------------
# check_escalation
# ---------------------------------------------------------------------------

class TestCheckEscalation:
    def _opts(self) -> EscalationOptions:
        return EscalationOptions.from_dict({
            "enabled": True,
            "levels": [
                {"after_failures": 1, "channels": ["slack"], "message_prefix": "[WARN]"},
                {"after_failures": 3, "channels": ["slack", "email"], "message_prefix": "[CRIT]"},
            ],
        })

    def test_disabled_returns_not_triggered(self):
        opts = EscalationOptions(enabled=False, levels=[])
        result = check_escalation(opts, 10)
        assert result.triggered is False
        assert result.level is None

    def test_zero_failures_no_trigger(self):
        result = check_escalation(self._opts(), 0)
        assert result.triggered is False

    def test_one_failure_hits_first_level(self):
        result = check_escalation(self._opts(), 1)
        assert result.triggered is True
        assert result.level is not None
        assert result.level.after_failures == 1
        assert "slack" in result.level.channels

    def test_three_failures_hits_second_level(self):
        result = check_escalation(self._opts(), 3)
        assert result.triggered is True
        assert result.level.after_failures == 3
        assert "email" in result.level.channels

    def test_summary_triggered(self):
        result = check_escalation(self._opts(), 3)
        text = result.summary()
        assert "[CRIT]" in text
        assert "email" in text

    def test_summary_not_triggered(self):
        result = check_escalation(self._opts(), 0)
        assert "No escalation" in result.summary()


# ---------------------------------------------------------------------------
# escalation_tracker
# ---------------------------------------------------------------------------

class TestEscalationTracker:
    def test_load_missing_returns_zero(self, tmp_path: Path):
        assert load_consecutive_failures("job", tmp_path) == 0

    def test_save_and_load_roundtrip(self, tmp_path: Path):
        save_consecutive_failures("myjob", 4, tmp_path)
        assert load_consecutive_failures("myjob", tmp_path) == 4

    def test_reset_removes_state(self, tmp_path: Path):
        save_consecutive_failures("myjob", 3, tmp_path)
        reset_consecutive_failures("myjob", tmp_path)
        assert load_consecutive_failures("myjob", tmp_path) == 0

    def test_update_increments_on_failure(self, tmp_path: Path):
        count = update_consecutive_failures("job", _make_result(False), tmp_path)
        assert count == 1
        count = update_consecutive_failures("job", _make_result(False), tmp_path)
        assert count == 2

    def test_update_resets_on_success(self, tmp_path: Path):
        save_consecutive_failures("job", 5, tmp_path)
        count = update_consecutive_failures("job", _make_result(True), tmp_path)
        assert count == 0
        assert load_consecutive_failures("job", tmp_path) == 0

    def test_path_sanitizes_slashes(self, tmp_path: Path):
        save_consecutive_failures("a/b/c", 2, tmp_path)
        assert load_consecutive_failures("a/b/c", tmp_path) == 2
