"""Integration-style tests: escalation_tracker feeding check_escalation."""

from __future__ import annotations

from pathlib import Path

from cronwatch.escalation import EscalationOptions, check_escalation
from cronwatch.escalation_tracker import update_consecutive_failures
from cronwatch.runner import JobResult


def _result(success: bool) -> JobResult:
    return JobResult(
        command="backup.sh",
        returncode=0 if success else 1,
        stdout="",
        stderr="disk full" if not success else "",
        duration=0.5,
        timed_out=False,
    )


def _opts() -> EscalationOptions:
    return EscalationOptions.from_dict({
        "enabled": True,
        "levels": [
            {"after_failures": 1, "channels": ["slack"]},
            {"after_failures": 3, "channels": ["slack", "email"]},
        ],
    })


def test_no_escalation_on_first_success(tmp_path: Path):
    count = update_consecutive_failures("backup", _result(True), tmp_path)
    result = check_escalation(_opts(), count)
    assert result.triggered is False


def test_escalation_after_repeated_failures(tmp_path: Path):
    opts = _opts()
    for i in range(1, 4):
        count = update_consecutive_failures("backup", _result(False), tmp_path)
        esc = check_escalation(opts, count)
        assert esc.triggered is True
        if i < 3:
            assert esc.level.after_failures == 1
        else:
            assert esc.level.after_failures == 3
            assert "email" in esc.level.channels


def test_escalation_resets_after_success(tmp_path: Path):
    opts = _opts()
    for _ in range(3):
        update_consecutive_failures("backup", _result(False), tmp_path)
    count = update_consecutive_failures("backup", _result(True), tmp_path)
    result = check_escalation(opts, count)
    assert result.triggered is False
    assert count == 0
