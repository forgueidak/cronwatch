"""Tests for cronwatch.export."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from cronwatch.digest import DigestEntry
from cronwatch.export import (
    ExportOptions,
    export_to_csv,
    export_to_json,
    run_export,
)
from cronwatch.runner import JobResult


def _make_entry(success: bool = True, stderr: str = "") -> DigestEntry:
    ts = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    return DigestEntry(
        job_name="backup",
        timestamp=ts,
        success=success,
        exit_code=0 if success else 1,
        duration=1.5,
        stderr=stderr,
    )


def _make_result(success: bool = True) -> JobResult:
    return JobResult(
        job_name="backup",
        command="/usr/bin/backup.sh",
        success=success,
        exit_code=0 if success else 1,
        stdout="",
        stderr="" if success else "disk full",
        duration=1.5,
        timestamp=datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc),
    )


def test_export_to_csv_empty():
    assert export_to_csv([]) == ""


def test_export_to_csv_headers():
    result = export_to_csv([_make_entry()])
    first_line = result.splitlines()[0]
    assert "job_name" in first_line
    assert "timestamp" in first_line
    assert "success" in first_line
    assert "exit_code" in first_line


def test_export_to_csv_row_count():
    entries = [_make_entry(), _make_entry(success=False)]
    lines = export_to_csv(entries).strip().splitlines()
    # 1 header + 2 data rows
    assert len(lines) == 3


def test_export_to_csv_failure_row_contains_stderr():
    entry = _make_entry(success=False, stderr="disk full")
    csv_text = export_to_csv([entry])
    assert "disk full" in csv_text


def test_export_to_json_empty():
    result = export_to_json([])
    assert json.loads(result) == []


def test_export_to_json_structure():
    entry = _make_entry()
    data = json.loads(export_to_json([entry]))
    assert len(data) == 1
    assert data[0]["job_name"] == "backup"
    assert data[0]["success"] is True
    assert "timestamp" in data[0]


def test_export_to_json_duration_rounded():
    entry = _make_entry()
    entry = DigestEntry(
        job_name=entry.job_name,
        timestamp=entry.timestamp,
        success=entry.success,
        exit_code=entry.exit_code,
        duration=1.123456789,
        stderr=entry.stderr,
    )
    data = json.loads(export_to_json([entry]))
    assert data[0]["duration"] == 1.123


def test_run_export_csv(tmp_path):
    results = [_make_result(), _make_result(success=False)]
    with patch("cronwatch.export.load_history", return_value=results):
        opts = ExportOptions(job_name="backup", fmt="csv", history_dir=str(tmp_path))
        output = run_export(opts)
    assert "backup" in output
    assert output.splitlines()[0].startswith("job_name")


def test_run_export_json(tmp_path):
    results = [_make_result()]
    with patch("cronwatch.export.load_history", return_value=results):
        opts = ExportOptions(job_name="backup", fmt="json", history_dir=str(tmp_path))
        output = run_export(opts)
    data = json.loads(output)
    assert isinstance(data, list)
    assert data[0]["job_name"] == "backup"
