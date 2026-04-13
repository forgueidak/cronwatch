"""Tests for cronwatch.digest module."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from cronwatch.digest import DigestEntry, build_digest, format_digest_text
from cronwatch.runner import JobResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_result(command: str, success: bool, offset: float = 0.0) -> JobResult:
    started = time.time() - offset
    return JobResult(
        command=command,
        returncode=0 if success else 1,
        stdout="ok" if success else "",
        stderr="" if success else "error",
        started_at=started,
        duration=0.5,
    )


def _write_history(log_dir: Path, result: JobResult) -> None:
    """Replicate the storage format used by cronwatch.history.record_result."""
    import hashlib
    key = hashlib.md5(result.command.encode()).hexdigest()[:10]
    hist_file = log_dir / f"{key}.jsonl"
    with hist_file.open("a") as fh:
        fh.write(json.dumps(result.__dict__) + "\n")


# ---------------------------------------------------------------------------
# DigestEntry
# ---------------------------------------------------------------------------

class TestDigestEntry:
    def test_success_rate_all_pass(self):
        e = DigestEntry("cmd", total_runs=10, failures=0, last_status="OK", last_run="now")
        assert e.success_rate == 100.0

    def test_success_rate_partial(self):
        e = DigestEntry("cmd", total_runs=4, failures=1, last_status="FAILED", last_run="now")
        assert e.success_rate == 75.0

    def test_success_rate_zero_runs(self):
        e = DigestEntry("cmd", total_runs=0, failures=0, last_status="OK", last_run="now")
        assert e.success_rate == 0.0


# ---------------------------------------------------------------------------
# build_digest
# ---------------------------------------------------------------------------

class TestBuildDigest:
    def test_returns_entry_per_command(self, tmp_path):
        for cmd in ["backup.sh", "cleanup.sh"]:
            _write_history(tmp_path, _make_result(cmd, success=True))
        entries = build_digest(["backup.sh", "cleanup.sh"], log_dir=str(tmp_path))
        assert len(entries) == 2

    def test_skips_commands_with_no_history(self, tmp_path):
        entries = build_digest(["ghost.sh"], log_dir=str(tmp_path))
        assert entries == []

    def test_failure_count_correct(self, tmp_path):
        cmd = "flaky.sh"
        _write_history(tmp_path, _make_result(cmd, success=True, offset=10))
        _write_history(tmp_path, _make_result(cmd, success=False, offset=5))
        _write_history(tmp_path, _make_result(cmd, success=False, offset=0))
        entries = build_digest([cmd], log_dir=str(tmp_path))
        assert entries[0].failures == 2
        assert entries[0].total_runs == 3

    def test_last_status_reflects_newest(self, tmp_path):
        cmd = "job.sh"
        _write_history(tmp_path, _make_result(cmd, success=False, offset=10))
        _write_history(tmp_path, _make_result(cmd, success=True, offset=0))
        entries = build_digest([cmd], log_dir=str(tmp_path))
        assert entries[0].last_status == "OK"


# ---------------------------------------------------------------------------
# format_digest_text
# ---------------------------------------------------------------------------

class TestFormatDigestText:
    def test_empty_entries_returns_placeholder(self):
        text = format_digest_text([])
        assert "No job history" in text

    def test_contains_command_name(self):
        e = DigestEntry("backup.sh", 5, 1, "OK", "2024-01-01 00:00 UTC")
        text = format_digest_text([e])
        assert "backup.sh" in text

    def test_failure_shows_cross_icon(self):
        e = DigestEntry("bad.sh", 3, 3, "FAILED", "2024-01-01 00:00 UTC")
        text = format_digest_text([e])
        assert "❌" in text

    def test_success_shows_check_icon(self):
        e = DigestEntry("good.sh", 3, 0, "OK", "2024-01-01 00:00 UTC")
        text = format_digest_text([e])
        assert "✅" in text
