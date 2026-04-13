"""Tests for cronwatch.summary."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

from cronwatch.digest import DigestEntry
from cronwatch.summary import SummaryOptions, build_summary, format_summary_text


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_result(success: bool, duration: float = 1.0, command: str = "echo hi"):
    """Return a minimal history-record dict."""
    return {
        "timestamp": time.time(),
        "command": command,
        "success": success,
        "duration": duration,
        "exit_code": 0 if success else 1,
        "stdout": "",
        "stderr": "" if success else "error",
    }


def _write_history(tmp_path: Path, job_name: str, records: list, monkeypatch) -> None:
    history_dir = tmp_path / "history"
    history_dir.mkdir(parents=True, exist_ok=True)
    history_file = history_dir / f"{job_name}.jsonl"
    with history_file.open("w") as fh:
        for rec in records:
            fh.write(json.dumps(rec) + "\n")
    monkeypatch.setattr(
        "cronwatch.history.HISTORY_DIR",
        history_dir,
    )


# ---------------------------------------------------------------------------
# build_summary
# ---------------------------------------------------------------------------

def test_build_summary_empty_history(tmp_path, monkeypatch):
    _write_history(tmp_path, "myjob", [], monkeypatch)
    opts = SummaryOptions(job_name="myjob")
    entries = build_summary(opts)
    assert entries == []


def test_build_summary_respects_limit(tmp_path, monkeypatch):
    records = [_make_result(True) for _ in range(10)]
    _write_history(tmp_path, "myjob", records, monkeypatch)
    opts = SummaryOptions(job_name="myjob", limit=5)
    entries = build_summary(opts)
    assert len(entries) == 5


def test_build_summary_since_filters(tmp_path, monkeypatch):
    old_rec = _make_result(True)
    old_rec["timestamp"] = 1_000_000.0  # very old
    recent_rec = _make_result(False)
    recent_rec["timestamp"] = time.time()
    _write_history(tmp_path, "myjob", [old_rec, recent_rec], monkeypatch)

    since = datetime(2020, 1, 1, tzinfo=timezone.utc)
    opts = SummaryOptions(job_name="myjob", since=since)
    entries = build_summary(opts)
    # old_rec has timestamp < 2020-01-01 epoch; recent_rec should survive
    assert all(e.timestamp >= since.timestamp() for e in entries)


# ---------------------------------------------------------------------------
# format_summary_text
# ---------------------------------------------------------------------------

def test_format_summary_text_no_entries():
    text = format_summary_text([], "emptyjob")
    assert "emptyjob" in text
    assert "No history" in text


def test_format_summary_text_contains_job_name():
    entry = DigestEntry(
        timestamp=time.time(),
        command="echo hello",
        success=True,
        duration=0.5,
        exit_code=0,
        stderr="",
    )
    text = format_summary_text([entry], "testjob")
    assert "testjob" in text
    assert "OK" in text
    assert "echo hello" in text


def test_format_summary_text_truncates_long_command():
    long_cmd = "python " + "x" * 50
    entry = DigestEntry(
        timestamp=time.time(),
        command=long_cmd,
        success=False,
        duration=2.3,
        exit_code=1,
        stderr="boom",
    )
    text = format_summary_text([entry], "longjob")
    assert "..." in text
    assert "FAIL" in text
