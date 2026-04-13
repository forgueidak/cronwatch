"""Tests for cronwatch.ratelimit."""
from __future__ import annotations

import time
from pathlib import Path

import pytest

from cronwatch.ratelimit import (
    RateLimitOptions,
    RateLimitState,
    _state_path,
    is_allowed,
    load_rate_limit_state,
    save_rate_limit_state,
)


@pytest.fixture()
def state_dir(tmp_path: Path) -> Path:
    return tmp_path / "ratelimit"


def test_load_missing_returns_empty_state(state_dir: Path) -> None:
    state = load_rate_limit_state("myjob", state_dir)
    assert state.job_name == "myjob"
    assert state.timestamps == []


def test_save_and_load_roundtrip(state_dir: Path) -> None:
    state = RateLimitState(job_name="backup", timestamps=[1000.0, 2000.0])
    save_rate_limit_state(state, state_dir)
    loaded = load_rate_limit_state("backup", state_dir)
    assert loaded.job_name == "backup"
    assert loaded.timestamps == [1000.0, 2000.0]


def test_save_creates_parent_directory(state_dir: Path) -> None:
    assert not state_dir.exists()
    state = RateLimitState(job_name="job")
    save_rate_limit_state(state, state_dir)
    assert state_dir.exists()


def test_state_path_sanitizes_slashes(state_dir: Path) -> None:
    path = _state_path("/etc/cron/job", state_dir)
    assert "/" not in path.name


def test_prune_removes_old_timestamps() -> None:
    old = time.time() - 7200
    recent = time.time() - 10
    state = RateLimitState(job_name="j", timestamps=[old, recent])
    state.prune(3600)
    assert len(state.timestamps) == 1
    assert state.timestamps[0] == recent


def test_count_in_window(state_dir: Path) -> None:
    now = time.time()
    state = RateLimitState(job_name="j", timestamps=[now - 100, now - 200, now - 9000])
    assert state.count_in_window(3600) == 2


def test_is_allowed_disabled_always_true(state_dir: Path) -> None:
    opts = RateLimitOptions(enabled=False)
    for _ in range(20):
        assert is_allowed("job", opts, state_dir) is True


def test_is_allowed_under_limit(state_dir: Path) -> None:
    opts = RateLimitOptions(enabled=True, max_per_hour=3, max_per_day=10)
    assert is_allowed("job", opts, state_dir) is True
    assert is_allowed("job", opts, state_dir) is True
    assert is_allowed("job", opts, state_dir) is True


def test_is_allowed_blocks_at_hourly_limit(state_dir: Path) -> None:
    opts = RateLimitOptions(enabled=True, max_per_hour=2, max_per_day=100)
    assert is_allowed("job", opts, state_dir) is True
    assert is_allowed("job", opts, state_dir) is True
    assert is_allowed("job", opts, state_dir) is False


def test_is_allowed_blocks_at_daily_limit(state_dir: Path) -> None:
    opts = RateLimitOptions(enabled=True, max_per_hour=100, max_per_day=3, window_seconds=3600)
    # Inject old hourly timestamps but recent daily ones
    state = RateLimitState(job_name="job", timestamps=[time.time() - 100] * 3)
    save_rate_limit_state(state, state_dir)
    assert is_allowed("job", opts, state_dir) is False


def test_is_allowed_records_timestamp(state_dir: Path) -> None:
    opts = RateLimitOptions(enabled=True, max_per_hour=10, max_per_day=50)
    is_allowed("job", opts, state_dir)
    state = load_rate_limit_state("job", state_dir)
    assert len(state.timestamps) == 1
