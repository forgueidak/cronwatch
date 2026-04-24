"""Tests for cronwatch/drain.py"""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from cronwatch.drain import (
    DrainOptions,
    DrainState,
    _state_path,
    begin_drain,
    clear_drain_state,
    end_drain,
    is_draining,
    load_drain_state,
    save_drain_state,
)


@pytest.fixture()
def state_dir(tmp_path: Path) -> str:
    return str(tmp_path / "drain")


def _opts(state_dir: str, enabled: bool = True, timeout: int = 300) -> DrainOptions:
    return DrainOptions(enabled=enabled, state_dir=state_dir, drain_timeout_seconds=timeout)


# ---------------------------------------------------------------------------
# DrainOptions.from_dict
# ---------------------------------------------------------------------------

class TestDrainOptionsFromDict:
    def test_defaults(self):
        opts = DrainOptions.from_dict({})
        assert opts.enabled is False
        assert opts.state_dir == "/tmp/cronwatch/drain"
        assert opts.drain_timeout_seconds == 300

    def test_full(self):
        opts = DrainOptions.from_dict(
            {"drain": {"enabled": True, "state_dir": "/var/drain", "drain_timeout_seconds": 60}}
        )
        assert opts.enabled is True
        assert opts.state_dir == "/var/drain"
        assert opts.drain_timeout_seconds == 60

    def test_enabled_coerced(self):
        opts = DrainOptions.from_dict({"drain": {"enabled": 1}})
        assert opts.enabled is True


# ---------------------------------------------------------------------------
# state path sanitisation
# ---------------------------------------------------------------------------

def test_state_path_sanitizes_slashes(tmp_path):
    p = _state_path(str(tmp_path), "my/job name")
    assert "/" not in p.name
    assert " " not in p.name


# ---------------------------------------------------------------------------
# load / save / clear
# ---------------------------------------------------------------------------

def test_load_drain_state_missing(state_dir):
    s = load_drain_state(state_dir, "myjob")
    assert s.draining is False
    assert s.started_at is None


def test_save_and_load_roundtrip(state_dir):
    original = DrainState(draining=True, started_at=1_000_000.0, job_name="myjob")
    save_drain_state(state_dir, "myjob", original)
    loaded = load_drain_state(state_dir, "myjob")
    assert loaded.draining is True
    assert loaded.started_at == pytest.approx(1_000_000.0)
    assert loaded.job_name == "myjob"


def test_save_creates_parent_directory(tmp_path):
    nested = str(tmp_path / "a" / "b" / "c")
    save_drain_state(nested, "job", DrainState(draining=True))
    assert Path(nested).exists()


def test_clear_removes_file(state_dir):
    save_drain_state(state_dir, "job", DrainState(draining=True))
    clear_drain_state(state_dir, "job")
    assert not _state_path(state_dir, "job").exists()


def test_clear_missing_file_is_noop(state_dir):
    clear_drain_state(state_dir, "nonexistent")  # should not raise


# ---------------------------------------------------------------------------
# is_draining / begin_drain / end_drain
# ---------------------------------------------------------------------------

def test_is_draining_disabled_always_false(state_dir):
    opts = _opts(state_dir, enabled=False)
    begin_drain(opts, "job")  # state written but disabled
    assert is_draining(opts, "job") is False


def test_begin_drain_sets_draining_true(state_dir):
    opts = _opts(state_dir)
    begin_drain(opts, "job")
    assert is_draining(opts, "job") is True


def test_end_drain_clears_state(state_dir):
    opts = _opts(state_dir)
    begin_drain(opts, "job")
    end_drain(opts, "job")
    assert is_draining(opts, "job") is False


def test_is_draining_expired_timeout(state_dir):
    opts = _opts(state_dir, timeout=1)
    state = DrainState(draining=True, started_at=time.time() - 10, job_name="job")
    save_drain_state(state_dir, "job", state)
    assert is_draining(opts, "job") is False
    # state file should be cleared
    assert not _state_path(state_dir, "job").exists()


def test_is_draining_not_expired(state_dir):
    opts = _opts(state_dir, timeout=300)
    state = DrainState(draining=True, started_at=time.time(), job_name="job")
    save_drain_state(state_dir, "job", state)
    assert is_draining(opts, "job") is True
