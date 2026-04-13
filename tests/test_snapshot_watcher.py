"""Tests for cronwatch.snapshot_watcher."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import pytest

from cronwatch.snapshot import save_snapshot
from cronwatch.snapshot_watcher import (
    SnapshotCheckResult,
    SnapshotOptions,
    check_snapshot,
    format_change_notice,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_result(command="echo hi", stdout="hi\n", returncode=0):
    """Build a minimal JobResult-like object."""
    from cronwatch.runner import JobResult
    return JobResult(
        command=command,
        returncode=returncode,
        stdout=stdout,
        stderr="",
        duration=0.1,
    )


# ---------------------------------------------------------------------------
# check_snapshot — disabled
# ---------------------------------------------------------------------------

def test_check_snapshot_disabled_returns_none(tmp_path):
    opts = SnapshotOptions(enabled=False, dir=tmp_path)
    result = check_snapshot(_make_result(), opts)
    assert result is None


def test_check_snapshot_skips_failed_job(tmp_path):
    opts = SnapshotOptions(enabled=True, dir=tmp_path)
    result = check_snapshot(_make_result(returncode=1), opts)
    assert result is None


# ---------------------------------------------------------------------------
# check_snapshot — first run (no prior snapshot)
# ---------------------------------------------------------------------------

def test_check_snapshot_first_run_changed_true(tmp_path):
    opts = SnapshotOptions(enabled=True, dir=tmp_path)
    snap = check_snapshot(_make_result(), opts)
    assert snap is not None
    assert snap.changed is True
    assert snap.previous_exists is False


def test_check_snapshot_first_run_should_notify_when_enabled(tmp_path):
    opts = SnapshotOptions(enabled=True, notify_on_change=True, dir=tmp_path)
    snap = check_snapshot(_make_result(), opts)
    assert snap.should_notify is True


def test_check_snapshot_first_run_no_notify_when_disabled(tmp_path):
    opts = SnapshotOptions(enabled=True, notify_on_change=False, dir=tmp_path)
    snap = check_snapshot(_make_result(), opts)
    assert snap.should_notify is False


# ---------------------------------------------------------------------------
# check_snapshot — subsequent runs
# ---------------------------------------------------------------------------

def test_check_snapshot_same_output_not_changed(tmp_path):
    save_snapshot("echo hi", "hi\n", base_dir=tmp_path)
    opts = SnapshotOptions(enabled=True, dir=tmp_path)
    snap = check_snapshot(_make_result(stdout="hi\n"), opts)
    assert snap.changed is False
    assert snap.should_notify is False


def test_check_snapshot_different_output_changed(tmp_path):
    save_snapshot("echo hi", "old\n", base_dir=tmp_path)
    opts = SnapshotOptions(enabled=True, notify_on_change=True, dir=tmp_path)
    snap = check_snapshot(_make_result(stdout="new\n"), opts)
    assert snap.changed is True
    assert snap.should_notify is True


# ---------------------------------------------------------------------------
# format_change_notice
# ---------------------------------------------------------------------------

def test_format_change_notice_empty_when_not_changed():
    snap = SnapshotCheckResult(changed=False, previous_exists=True, should_notify=False)
    assert format_change_notice(_make_result(), snap) == ""


def test_format_change_notice_first_snapshot_message():
    snap = SnapshotCheckResult(changed=True, previous_exists=False, should_notify=True)
    msg = format_change_notice(_make_result(command="myjob"), snap)
    assert "First snapshot" in msg
    assert "myjob" in msg


def test_format_change_notice_change_message():
    snap = SnapshotCheckResult(changed=True, previous_exists=True, should_notify=True)
    result = _make_result(command="myjob", stdout="new output")
    msg = format_change_notice(result, snap)
    assert "Output changed" in msg
    assert "new output" in msg
