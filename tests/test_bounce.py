"""Tests for cronwatch/bounce.py"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

import pytest

from cronwatch.bounce import (
    BounceOptions,
    BounceState,
    _state_path,
    check_bounce,
    load_bounce_state,
    save_bounce_state,
)
from cronwatch.runner import JobResult


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _make_result(command: str = "echo hi", exit_code: int = 0) -> JobResult:
    return JobResult(
        command=command,
        exit_code=exit_code,
        stdout="",
        stderr="",
        duration=0.1,
        timed_out=False,
    )


def _opts(tmp_path: Path, **kwargs) -> BounceOptions:
    defaults = dict(enabled=True, window_seconds=300, min_flaps=3, state_dir=str(tmp_path))
    defaults.update(kwargs)
    return BounceOptions(**defaults)


# ---------------------------------------------------------------------------
# BounceOptions.from_dict
# ---------------------------------------------------------------------------

class TestBounceOptionsFromDict:
    def test_defaults(self):
        opts = BounceOptions.from_dict({})
        assert opts.enabled is False
        assert opts.window_seconds == 300
        assert opts.min_flaps == 3

    def test_full(self):
        opts = BounceOptions.from_dict({"bounce": {"enabled": True, "window_seconds": 60, "min_flaps": 2}})
        assert opts.enabled is True
        assert opts.window_seconds == 60
        assert opts.min_flaps == 2

    def test_enabled_coerced_to_bool(self):
        opts = BounceOptions.from_dict({"bounce": {"enabled": 1}})
        assert opts.enabled is True


# ---------------------------------------------------------------------------
# state path sanitisation
# ---------------------------------------------------------------------------

def test_state_path_sanitizes_slashes(tmp_path):
    p = _state_path(str(tmp_path), "my/job name")
    assert "/" not in p.name
    assert " " not in p.name


# ---------------------------------------------------------------------------
# save / load roundtrip
# ---------------------------------------------------------------------------

def test_save_and_load_roundtrip(tmp_path):
    state = BounceState(transitions=[1.0, 2.0, 3.0])
    save_bounce_state(str(tmp_path), "myjob", state)
    loaded = load_bounce_state(str(tmp_path), "myjob")
    assert loaded.transitions == [1.0, 2.0, 3.0]


def test_load_missing_returns_empty(tmp_path):
    state = load_bounce_state(str(tmp_path), "nonexistent")
    assert state.transitions == []


def test_save_creates_parent_directory(tmp_path):
    nested = tmp_path / "deep" / "dir"
    save_bounce_state(str(nested), "job", BounceState(transitions=[1.0]))
    assert (nested / "job.bounce.json").exists()


# ---------------------------------------------------------------------------
# check_bounce
# ---------------------------------------------------------------------------

def test_check_bounce_disabled_returns_none(tmp_path):
    opts = _opts(tmp_path, enabled=False)
    result = check_bounce(_make_result(), opts)
    assert result is None


def test_check_bounce_below_threshold_not_flapping(tmp_path):
    opts = _opts(tmp_path, min_flaps=3, window_seconds=300)
    now = time.time()
    r = check_bounce(_make_result(), opts, _now=now)
    assert r is not None
    assert r.flapping is False
    assert r.flap_count == 1


def test_check_bounce_reaches_threshold(tmp_path):
    opts = _opts(tmp_path, min_flaps=3, window_seconds=300)
    now = time.time()
    for _ in range(3):
        r = check_bounce(_make_result(), opts, _now=now)
    assert r.flapping is True
    assert r.flap_count == 3


def test_check_bounce_prunes_old_transitions(tmp_path):
    opts = _opts(tmp_path, min_flaps=2, window_seconds=60)
    old_time = time.time() - 120  # outside window
    # seed two old transitions
    state = BounceState(transitions=[old_time, old_time])
    save_bounce_state(str(tmp_path), "echo hi", state)

    now = time.time()
    r = check_bounce(_make_result(), opts, _now=now)
    # old ones pruned; only 1 new transition recorded => not flapping
    assert r.flapping is False
    assert r.flap_count == 1


def test_check_bounce_message_contains_job_name(tmp_path):
    opts = _opts(tmp_path, min_flaps=1)
    r = check_bounce(_make_result(command="backup.sh"), opts)
    assert "backup.sh" in r.message
