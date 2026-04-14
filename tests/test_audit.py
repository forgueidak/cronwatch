"""Tests for cronwatch.audit."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from cronwatch.audit import (
    AuditEntry,
    _audit_path,
    load_audit_log,
    record_audit,
)


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def log_dir(tmp_path: Path) -> str:
    return str(tmp_path / "audit")


# ── AuditEntry ────────────────────────────────────────────────────────────────

class TestAuditEntry:
    def test_to_dict_round_trip(self):
        e = AuditEntry(
            timestamp="2024-01-01T00:00:00+00:00",
            event="job_run",
            job="backup",
            actor="cronwatch",
            detail={"exit_code": 0},
        )
        d = e.to_dict()
        restored = AuditEntry.from_dict(d)
        assert restored.event == e.event
        assert restored.detail == e.detail

    def test_from_dict_defaults(self):
        e = AuditEntry.from_dict({"timestamp": "t", "event": "x", "job": "j"})
        assert e.actor == "cronwatch"
        assert e.detail == {}


# ── _audit_path ───────────────────────────────────────────────────────────────

def test_audit_path_sanitizes_slashes(tmp_path):
    p = _audit_path(str(tmp_path), "/etc/cron.d/backup")
    assert "/" not in p.name


# ── record_audit ──────────────────────────────────────────────────────────────

def test_record_creates_file(log_dir):
    record_audit(log_dir, "job_run", "myjob")
    assert any(Path(log_dir).iterdir())


def test_record_appends_valid_json(log_dir):
    record_audit(log_dir, "job_run", "myjob", detail={"exit_code": 0})
    record_audit(log_dir, "alert_sent", "myjob", detail={"channel": "#ops"})
    path = _audit_path(log_dir, "myjob")
    lines = [l for l in path.read_text().splitlines() if l.strip()]
    assert len(lines) == 2
    for line in lines:
        obj = json.loads(line)
        assert "timestamp" in obj
        assert "event" in obj


def test_record_returns_entry(log_dir):
    entry = record_audit(log_dir, "lock_acquired", "myjob")
    assert isinstance(entry, AuditEntry)
    assert entry.event == "lock_acquired"


# ── load_audit_log ────────────────────────────────────────────────────────────

def test_load_missing_returns_empty(log_dir):
    assert load_audit_log(log_dir, "nonexistent") == []


def test_load_returns_newest_first(log_dir):
    for ev in ("job_run", "alert_sent", "retry"):
        record_audit(log_dir, ev, "myjob")
    entries = load_audit_log(log_dir, "myjob")
    assert entries[0].event == "retry"
    assert entries[-1].event == "job_run"


def test_load_skips_corrupt_lines(log_dir):
    path = _audit_path(log_dir, "myjob")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('{"timestamp":"t","event":"job_run","job":"myjob","actor":"cw","detail":{}}\nNOT_JSON\n')
    entries = load_audit_log(log_dir, "myjob")
    assert len(entries) == 1
