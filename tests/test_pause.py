"""Tests for cronwatch/pause.py"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from cronwatch.pause import (
    PauseOptions,
    PauseState,
    _state_path,
    is_paused,
    load_pause_state,
    pause_job,
    resume_job,
    save_pause_state,
)


@pytest.fixture()
def state_dir(tmp_path: Path) -> str:
    return str(tmp_path / "pause")


def test_load_pause_state_missing(state_dir: str) -> None:
    state = load_pause_state("myjob", state_dir)
    assert state.paused is False
    assert state.reason == ""


def test_save_and_load_roundtrip(state_dir: str) -> None:
    s = PauseState(paused=True, reason="maintenance", resume_after=None,
                   paused_at="2025-01-01T00:00:00+00:00")
    save_pause_state("myjob", s, state_dir)
    loaded = load_pause_state("myjob", state_dir)
    assert loaded.paused is True
    assert loaded.reason == "maintenance"


def test_save_creates_parent_directory(tmp_path: Path) -> None:
    d = str(tmp_path / "deep" / "nested")
    save_pause_state("job", PauseState(), d)
    assert Path(d).exists()


def test_state_path_sanitizes_slashes(state_dir: str) -> None:
    p = _state_path("a/b/c", state_dir)
    assert "/" not in p.name


def test_pause_job_sets_paused_true(state_dir: str) -> None:
    state = pause_job("myjob", reason="testing", state_dir=state_dir)
    assert state.paused is True
    assert state.reason == "testing"
    assert state.paused_at is not None


def test_resume_job_clears_pause(state_dir: str) -> None:
    pause_job("myjob", state_dir=state_dir)
    state = resume_job("myjob", state_dir=state_dir)
    assert state.paused is False
    assert is_paused("myjob", state_dir) is False


def test_is_paused_returns_true_when_paused(state_dir: str) -> None:
    pause_job("myjob", state_dir=state_dir)
    assert is_paused("myjob", state_dir) is True


def test_is_paused_returns_false_when_not_paused(state_dir: str) -> None:
    assert is_paused("myjob", state_dir) is False


def test_is_paused_auto_resumes_after_past_datetime(state_dir: str) -> None:
    past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    pause_job("myjob", resume_after=past, state_dir=state_dir)
    assert is_paused("myjob", state_dir) is False


def test_is_paused_stays_paused_before_resume_after(state_dir: str) -> None:
    future = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    pause_job("myjob", resume_after=future, state_dir=state_dir)
    assert is_paused("myjob", state_dir) is True


def test_pause_options_from_dict() -> None:
    opts = PauseOptions.from_dict({"enabled": False, "state_dir": "/tmp/p"})
    assert opts.enabled is False
    assert opts.state_dir == "/tmp/p"


def test_pause_state_to_dict_round_trip() -> None:
    s = PauseState(paused=True, paused_at="2025-01-01T00:00:00+00:00",
                   reason="test", resume_after="2025-06-01T00:00:00+00:00")
    assert PauseState.from_dict(s.to_dict()).reason == "test"
