"""Tests for cronwatch/mute.py"""
import json
import os
import time

import pytest

from cronwatch.mute import (
    MuteOptions,
    MuteState,
    _state_path,
    clear_mute_state,
    is_muted,
    load_mute_state,
    mute_job,
    save_mute_state,
)


@pytest.fixture()
def state_dir(tmp_path):
    return str(tmp_path / "mute")


def test_load_mute_state_missing(state_dir):
    state = load_mute_state(state_dir, "my_job")
    assert state.muted_until is None
    assert state.reason == ""


def test_save_and_load_roundtrip(state_dir):
    original = MuteState(muted_until=time.time() + 300, reason="maintenance")
    save_mute_state(state_dir, "my_job", original)
    loaded = load_mute_state(state_dir, "my_job")
    assert abs(loaded.muted_until - original.muted_until) < 1
    assert loaded.reason == "maintenance"


def test_save_creates_parent_directory(tmp_path):
    deep_dir = str(tmp_path / "a" / "b" / "mute")
    state = MuteState(muted_until=time.time() + 60)
    save_mute_state(deep_dir, "job", state)
    assert os.path.exists(_state_path(deep_dir, "job"))


def test_state_path_sanitizes_slashes(state_dir):
    path = _state_path(state_dir, "some/job/name")
    assert "/" not in os.path.basename(path)


def test_clear_removes_file(state_dir):
    save_mute_state(state_dir, "my_job", MuteState(muted_until=time.time() + 60))
    clear_mute_state(state_dir, "my_job")
    assert not os.path.exists(_state_path(state_dir, "my_job"))


def test_clear_missing_file_is_noop(state_dir):
    clear_mute_state(state_dir, "nonexistent_job")  # should not raise


def test_is_muted_active(state_dir):
    mute_job(state_dir, "my_job", duration_seconds=3600, reason="test")
    assert is_muted(state_dir, "my_job") is True


def test_is_muted_expired(state_dir):
    state = MuteState(muted_until=time.time() - 1, reason="old")
    save_mute_state(state_dir, "my_job", state)
    assert is_muted(state_dir, "my_job") is False


def test_is_muted_no_state(state_dir):
    assert is_muted(state_dir, "my_job") is False


def test_mute_job_returns_state(state_dir):
    state = mute_job(state_dir, "my_job", 120, reason="deploy")
    assert state.muted_until is not None
    assert state.reason == "deploy"
    assert state.muted_until > time.time()


def test_mute_options_from_dict():
    opts = MuteOptions.from_dict({"enabled": True, "state_dir": "/tmp/x"})
    assert opts.enabled is True
    assert opts.state_dir == "/tmp/x"


def test_mute_options_defaults():
    opts = MuteOptions.from_dict({})
    assert opts.enabled is False
    assert "mute" in opts.state_dir
