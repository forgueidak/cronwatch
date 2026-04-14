"""Tests for cronwatch.runlog."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cronwatch.runlog import (
    RunLogEntry,
    _runlog_path,
    load_run_log,
    save_run_log,
    update_run_log,
)
from cronwatch.runner import JobResult


def _make_result(command: str = "echo hi", returncode: int = 0) -> JobResult:
    return JobResult(
        command=command,
        returncode=returncode,
        stdout="ok",
        stderr="",
        duration=0.1,
        timed_out=False,
    )


@pytest.fixture()
def state_dir(tmp_path: Path) -> Path:
    return tmp_path / "state"


class TestRunLogEntry:
    def test_to_dict_round_trip(self):
        entry = RunLogEntry(command="ls", run_count=3, success_count=2, failure_count=1,
                            last_run="2024-01-01T00:00:00+00:00", last_status="failure")
        restored = RunLogEntry.from_dict(entry.to_dict())
        assert restored.command == entry.command
        assert restored.run_count == entry.run_count
        assert restored.success_count == entry.success_count
        assert restored.failure_count == entry.failure_count
        assert restored.last_status == entry.last_status

    def test_from_dict_defaults(self):
        entry = RunLogEntry.from_dict({"command": "ls"})
        assert entry.run_count == 0
        assert entry.last_run is None


def test_runlog_path_sanitizes_slashes(state_dir: Path):
    path = _runlog_path("/usr/bin/backup", state_dir)
    assert "/" not in path.name


def test_load_run_log_missing_returns_default(state_dir: Path):
    entry = load_run_log("nonexistent", state_dir)
    assert entry.run_count == 0
    assert entry.last_status is None


def test_save_creates_file(state_dir: Path):
    entry = RunLogEntry(command="echo", run_count=1, last_status="success")
    save_run_log(entry, state_dir)
    path = _runlog_path("echo", state_dir)
    assert path.exists()


def test_save_and_load_roundtrip(state_dir: Path):
    entry = RunLogEntry(command="backup", run_count=5, success_count=4, failure_count=1,
                        last_status="success")
    save_run_log(entry, state_dir)
    loaded = load_run_log("backup", state_dir)
    assert loaded.run_count == 5
    assert loaded.success_count == 4
    assert loaded.last_status == "success"


def test_update_run_log_success(state_dir: Path):
    result = _make_result(returncode=0)
    entry = update_run_log(result, state_dir)
    assert entry.run_count == 1
    assert entry.success_count == 1
    assert entry.failure_count == 0
    assert entry.last_status == "success"
    assert entry.last_run is not None


def test_update_run_log_failure(state_dir: Path):
    result = _make_result(returncode=1)
    entry = update_run_log(result, state_dir)
    assert entry.failure_count == 1
    assert entry.last_status == "failure"


def test_update_run_log_accumulates(state_dir: Path):
    cmd = "my-job"
    update_run_log(_make_result(command=cmd, returncode=0), state_dir)
    update_run_log(_make_result(command=cmd, returncode=1), state_dir)
    update_run_log(_make_result(command=cmd, returncode=0), state_dir)
    entry = load_run_log(cmd, state_dir)
    assert entry.run_count == 3
    assert entry.success_count == 2
    assert entry.failure_count == 1


def test_save_writes_valid_json(state_dir: Path):
    entry = RunLogEntry(command="cron", run_count=2)
    save_run_log(entry, state_dir)
    path = _runlog_path("cron", state_dir)
    data = json.loads(path.read_text())
    assert data["run_count"] == 2
