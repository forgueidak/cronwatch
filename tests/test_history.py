"""Tests for cronwatch.history module."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cronwatch.history import last_failure, load_history, record_result
from cronwatch.runner import JobResult


@pytest.fixture()
def history_file(tmp_path: Path) -> str:
    return str(tmp_path / "test_history.jsonl")


def _make_result(
    command: str = "echo hi",
    exit_code: int = 0,
    stdout: str = "",
    stderr: str = "",
    duration: float = 0.1,
    timed_out: bool = False,
) -> JobResult:
    return JobResult(
        command=command,
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        duration=duration,
        timed_out=timed_out,
    )


def test_record_creates_file(history_file: str) -> None:
    record_result(_make_result(), history_file=history_file)
    assert Path(history_file).exists()


def test_record_appends_valid_json(history_file: str) -> None:
    record_result(_make_result(exit_code=0), history_file=history_file)
    record_result(_make_result(exit_code=1), history_file=history_file)
    lines = Path(history_file).read_text().strip().splitlines()
    assert len(lines) == 2
    for line in lines:
        data = json.loads(line)
        assert "command" in data
        assert "timestamp" in data


def test_load_history_returns_newest_first(history_file: str) -> None:
    for code in (0, 1, 2):
        record_result(_make_result(exit_code=code), history_file=history_file)
    entries = load_history(history_file=history_file)
    assert entries[0]["exit_code"] == 2
    assert entries[-1]["exit_code"] == 0


def test_load_history_filters_by_command(history_file: str) -> None:
    record_result(_make_result(command="cmd_a"), history_file=history_file)
    record_result(_make_result(command="cmd_b"), history_file=history_file)
    results = load_history(command="cmd_a", history_file=history_file)
    assert all(e["command"] == "cmd_a" for e in results)
    assert len(results) == 1


def test_load_history_respects_limit(history_file: str) -> None:
    for _ in range(10):
        record_result(_make_result(), history_file=history_file)
    entries = load_history(limit=3, history_file=history_file)
    assert len(entries) == 3


def test_load_history_missing_file_returns_empty(tmp_path: Path) -> None:
    entries = load_history(history_file=str(tmp_path / "nonexistent.jsonl"))
    assert entries == []


def test_last_failure_returns_most_recent(history_file: str) -> None:
    record_result(_make_result(command="job", exit_code=0), history_file=history_file)
    record_result(_make_result(command="job", exit_code=1, stderr="oops"), history_file=history_file)
    entry = last_failure("job", history_file=history_file)
    assert entry is not None
    assert entry["exit_code"] == 1
    assert entry["stderr"] == "oops"


def test_last_failure_none_when_all_succeed(history_file: str) -> None:
    record_result(_make_result(command="ok", exit_code=0), history_file=history_file)
    assert last_failure("ok", history_file=history_file) is None


def test_last_failure_detects_timeout(history_file: str) -> None:
    record_result(
        _make_result(command="slow", exit_code=0, timed_out=True),
        history_file=history_file,
    )
    entry = last_failure("slow", history_file=history_file)
    assert entry is not None
    assert entry["timed_out"] is True
