"""Tests for cronwatch.report."""

from __future__ import annotations

import datetime
import json
from unittest.mock import patch

import pytest

from cronwatch.digest import DigestEntry
from cronwatch.report import ReportOptions, _filter_entries, build_report


def _make_entry(success: bool, minutes_ago: int = 0) -> DigestEntry:
    ts = datetime.datetime.utcnow() - datetime.timedelta(minutes=minutes_ago)
    return DigestEntry(
        timestamp=ts,
        success=success,
        duration=1.0,
        exit_code=0 if success else 1,
        stderr="" if success else "error",
    )


_SAMPLE_ENTRIES = [
    _make_entry(True, minutes_ago=30),
    _make_entry(False, minutes_ago=20),
    _make_entry(True, minutes_ago=10),
]


class TestFilterEntries:
    def test_no_since_returns_all(self):
        result = _filter_entries(_SAMPLE_ENTRIES, since=None)
        assert result == _SAMPLE_ENTRIES

    def test_since_filters_old_entries(self):
        cutoff = datetime.datetime.utcnow() - datetime.timedelta(minutes=25)
        result = _filter_entries(_SAMPLE_ENTRIES, since=cutoff)
        assert len(result) == 2

    def test_since_future_returns_empty(self):
        cutoff = datetime.datetime.utcnow() + datetime.timedelta(minutes=1)
        result = _filter_entries(_SAMPLE_ENTRIES, since=cutoff)
        assert result == []


class TestBuildReport:
    def _patch_history(self, entries):
        return patch("cronwatch.report.load_history", return_value=[])

    def test_no_history_returns_message(self):
        with patch("cronwatch.report.load_history", return_value=[]):
            with patch("cronwatch.report.build_digest", return_value=[]):
                opts = ReportOptions(job_name="backup")
                result = build_report(opts)
        assert "No history" in result
        assert "backup" in result

    def test_text_format_contains_job_name(self):
        with patch("cronwatch.report.load_history", return_value=[]):
            with patch("cronwatch.report.build_digest", return_value=_SAMPLE_ENTRIES):
                opts = ReportOptions(job_name="sync", format="text")
                result = build_report(opts)
        assert "sync" in result

    def test_json_format_is_valid_json(self):
        with patch("cronwatch.report.load_history", return_value=[]):
            with patch("cronwatch.report.build_digest", return_value=_SAMPLE_ENTRIES):
                opts = ReportOptions(job_name="cleanup", format="json")
                result = build_report(opts)
        data = json.loads(result)
        assert data["job"] == "cleanup"
        assert "success_rate" in data
        assert len(data["entries"]) == 3

    def test_json_format_success_rate_range(self):
        with patch("cronwatch.report.load_history", return_value=[]):
            with patch("cronwatch.report.build_digest", return_value=_SAMPLE_ENTRIES):
                opts = ReportOptions(job_name="job", format="json")
                data = json.loads(build_report(opts))
        assert 0.0 <= data["success_rate"] <= 1.0
