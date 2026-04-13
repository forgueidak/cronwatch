"""Tests for cronwatch.snapshot."""

import json
from pathlib import Path

import pytest

from cronwatch.snapshot import (
    Snapshot,
    _hash_output,
    _snapshot_path,
    load_snapshot,
    output_changed,
    save_snapshot,
)


@pytest.fixture()
def snap_dir(tmp_path: Path) -> Path:
    return tmp_path / "snapshots"


# ---------------------------------------------------------------------------
# _hash_output
# ---------------------------------------------------------------------------

def test_hash_output_deterministic():
    assert _hash_output("hello") == _hash_output("hello")


def test_hash_output_differs_for_different_input():
    assert _hash_output("hello") != _hash_output("world")


# ---------------------------------------------------------------------------
# save_snapshot
# ---------------------------------------------------------------------------

def test_save_snapshot_creates_file(snap_dir):
    save_snapshot("echo hi", "hi\n", base_dir=snap_dir)
    path = _snapshot_path("echo hi", snap_dir)
    assert path.exists()


def test_save_snapshot_valid_json(snap_dir):
    save_snapshot("echo hi", "hi\n", base_dir=snap_dir)
    path = _snapshot_path("echo hi", snap_dir)
    data = json.loads(path.read_text())
    assert "stdout_hash" in data
    assert "captured_at" in data
    assert data["command"] == "echo hi"


def test_save_snapshot_preview_truncated(snap_dir):
    long_output = "x" * 500
    snap = save_snapshot("cmd", long_output, base_dir=snap_dir)
    assert len(snap.stdout_preview) == 200


def test_save_snapshot_returns_snapshot_instance(snap_dir):
    snap = save_snapshot("ls", "file1\nfile2\n", base_dir=snap_dir)
    assert isinstance(snap, Snapshot)


# ---------------------------------------------------------------------------
# load_snapshot
# ---------------------------------------------------------------------------

def test_load_snapshot_missing_returns_none(snap_dir):
    result = load_snapshot("nonexistent", base_dir=snap_dir)
    assert result is None


def test_load_snapshot_roundtrip(snap_dir):
    save_snapshot("date", "Mon Jan  1", base_dir=snap_dir)
    snap = load_snapshot("date", base_dir=snap_dir)
    assert snap is not None
    assert snap.command == "date"
    assert snap.stdout_hash == _hash_output("Mon Jan  1")


# ---------------------------------------------------------------------------
# output_changed
# ---------------------------------------------------------------------------

def test_output_changed_true_when_no_snapshot(snap_dir):
    assert output_changed("cmd", "output", base_dir=snap_dir) is True


def test_output_changed_false_when_same(snap_dir):
    save_snapshot("cmd", "stable output", base_dir=snap_dir)
    assert output_changed("cmd", "stable output", base_dir=snap_dir) is False


def test_output_changed_true_when_different(snap_dir):
    save_snapshot("cmd", "old output", base_dir=snap_dir)
    assert output_changed("cmd", "new output", base_dir=snap_dir) is True


def test_output_changed_updates_after_save(snap_dir):
    save_snapshot("cmd", "v1", base_dir=snap_dir)
    save_snapshot("cmd", "v2", base_dir=snap_dir)
    assert output_changed("cmd", "v2", base_dir=snap_dir) is False
    assert output_changed("cmd", "v1", base_dir=snap_dir) is True
