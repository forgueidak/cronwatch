"""Tests for cronwatch.checkpoint."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from cronwatch.checkpoint import (
    CheckpointOptions,
    CheckpointResult,
    _checkpoint_path,
    load_checkpoint,
    save_checkpoint,
    update_checkpoint,
)
from cronwatch.runner import JobResult


@pytest.fixture()
def state_dir(tmp_path: Path) -> Path:
    return tmp_path / "checkpoints"


def _make_result(success: bool, command: str = "backup.sh") -> JobResult:
    return JobResult(
        command=command,
        returncode=0 if success else 1,
        stdout="ok",
        stderr="",
        duration=1.0,
        timed_out=False,
    )


def _opts(state_dir: Path, enabled: bool = True) -> CheckpointOptions:
    return CheckpointOptions(enabled=enabled, state_dir=state_dir)


# ---------------------------------------------------------------------------
# CheckpointOptions.from_dict
# ---------------------------------------------------------------------------

class TestCheckpointOptionsFromDict:
    def test_defaults(self):
        opts = CheckpointOptions.from_dict({})
        assert opts.enabled is False

    def test_full(self, state_dir):
        opts = CheckpointOptions.from_dict({"enabled": True, "state_dir": str(state_dir)})
        assert opts.enabled is True
        assert opts.state_dir == state_dir

    def test_enabled_coerced(self):
        opts = CheckpointOptions.from_dict({"enabled": 1})
        assert opts.enabled is True


# ---------------------------------------------------------------------------
# _checkpoint_path
# ---------------------------------------------------------------------------

def test_checkpoint_path_sanitizes_slashes(state_dir):
    p = _checkpoint_path(state_dir, "/usr/local/bin/job")
    assert "/" not in p.name


# ---------------------------------------------------------------------------
# save / load
# ---------------------------------------------------------------------------

def test_load_missing_returns_none(state_dir):
    assert load_checkpoint(state_dir, "job.sh") is None


def test_save_creates_file(state_dir):
    ts = datetime.now(timezone.utc)
    save_checkpoint(state_dir, "job.sh", ts)
    p = _checkpoint_path(state_dir, "job.sh")
    assert p.exists()


def test_save_load_roundtrip(state_dir):
    ts = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    save_checkpoint(state_dir, "job.sh", ts)
    loaded = load_checkpoint(state_dir, "job.sh")
    assert loaded is not None
    assert loaded == ts


def test_load_corrupt_file_returns_none(state_dir):
    state_dir.mkdir(parents=True, exist_ok=True)
    p = _checkpoint_path(state_dir, "job.sh")
    p.write_text("not json")
    assert load_checkpoint(state_dir, "job.sh") is None


# ---------------------------------------------------------------------------
# update_checkpoint
# ---------------------------------------------------------------------------

def test_update_disabled_does_not_write(state_dir):
    result = _make_result(success=True)
    opts = _opts(state_dir, enabled=False)
    cr = update_checkpoint(result, opts)
    assert cr.updated is False
    assert not list(state_dir.glob("*.json")) if state_dir.exists() else True


def test_update_success_writes_and_returns_updated(state_dir):
    result = _make_result(success=True)
    cr = update_checkpoint(result, _opts(state_dir))
    assert cr.updated is True
    assert cr.last_success is not None


def test_update_failure_does_not_write(state_dir):
    result = _make_result(success=False)
    cr = update_checkpoint(result, _opts(state_dir))
    assert cr.updated is False


def test_update_failure_returns_previous_checkpoint(state_dir):
    ts = datetime(2024, 1, 1, tzinfo=timezone.utc)
    save_checkpoint(state_dir, "backup.sh", ts)
    result = _make_result(success=False)
    cr = update_checkpoint(result, _opts(state_dir))
    assert cr.last_success == ts


# ---------------------------------------------------------------------------
# CheckpointResult.summary
# ---------------------------------------------------------------------------

def test_summary_updated():
    ts = datetime(2024, 6, 1, tzinfo=timezone.utc)
    cr = CheckpointResult(updated=True, last_success=ts)
    assert "updated" in cr.summary().lower()


def test_summary_no_checkpoint():
    cr = CheckpointResult(updated=False, last_success=None)
    assert "no checkpoint" in cr.summary().lower()
