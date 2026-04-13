"""Tests for cronwatch.alert throttling logic."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from cronwatch.alert import (
    AlertState,
    _state_path,
    clear_alert_state,
    load_alert_state,
    save_alert_state,
    should_alert,
)


@pytest.fixture()
def state_dir(tmp_path: Path) -> Path:
    return tmp_path / "alert_state"


# --- load / save / clear ---

def test_load_alert_state_missing(state_dir: Path) -> None:
    assert load_alert_state(state_dir, "backup") is None


def test_save_and_load_roundtrip(state_dir: Path) -> None:
    state = AlertState(job_name="backup", last_alerted_at=1234567890.0, consecutive_failures=3)
    save_alert_state(state_dir, state)
    loaded = load_alert_state(state_dir, "backup")
    assert loaded is not None
    assert loaded.job_name == "backup"
    assert loaded.last_alerted_at == pytest.approx(1234567890.0)
    assert loaded.consecutive_failures == 3


def test_save_creates_parent_directory(state_dir: Path) -> None:
    state = AlertState(job_name="myjob", last_alerted_at=0.0)
    save_alert_state(state_dir, state)
    assert state_dir.exists()


def test_clear_removes_file(state_dir: Path) -> None:
    state = AlertState(job_name="myjob", last_alerted_at=0.0)
    save_alert_state(state_dir, state)
    clear_alert_state(state_dir, "myjob")
    assert not _state_path(state_dir, "myjob").exists()


def test_clear_nonexistent_is_noop(state_dir: Path) -> None:
    clear_alert_state(state_dir, "ghost")  # must not raise


def test_load_corrupt_file_returns_none(state_dir: Path) -> None:
    state_dir.mkdir(parents=True)
    _state_path(state_dir, "bad").write_text("{not valid json")
    assert load_alert_state(state_dir, "bad") is None


# --- should_alert ---

def test_should_alert_first_failure(state_dir: Path) -> None:
    alert, state = should_alert(state_dir, "job", failed=True)
    assert alert is True
    assert state is not None
    assert state.consecutive_failures == 1


def test_should_alert_success_returns_false(state_dir: Path) -> None:
    alert, state = should_alert(state_dir, "job", failed=False)
    assert alert is False
    assert state is None


def test_should_alert_throttled_within_window(state_dir: Path) -> None:
    initial = AlertState(job_name="job", last_alerted_at=time.time(), consecutive_failures=1)
    save_alert_state(state_dir, initial)
    alert, state = should_alert(state_dir, "job", failed=True, throttle_seconds=3600)
    assert alert is False
    assert state is not None
    assert state.consecutive_failures == 2


def test_should_alert_fires_after_throttle_window(state_dir: Path) -> None:
    old_time = time.time() - 7200  # 2 hours ago
    initial = AlertState(job_name="job", last_alerted_at=old_time, consecutive_failures=2)
    save_alert_state(state_dir, initial)
    alert, state = should_alert(state_dir, "job", failed=True, throttle_seconds=3600)
    assert alert is True
    assert state is not None
    assert state.consecutive_failures == 3
    assert state.last_alerted_at > old_time
