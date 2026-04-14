"""Tests for cronwatch.quota."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from cronwatch.quota import (
    QuotaOptions,
    QuotaResult,
    QuotaState,
    _state_path,
    check_quota,
    load_quota_state,
    save_quota_state,
)


@pytest.fixture()
def state_dir(tmp_path: Path) -> Path:
    return tmp_path / "quota"


def _opts(state_dir: Path, max_runs: int = 3, window: int = 60) -> QuotaOptions:
    return QuotaOptions(enabled=True, max_runs=max_runs, window_seconds=window, state_dir=state_dir)


# ---------------------------------------------------------------------------
# QuotaOptions.from_dict
# ---------------------------------------------------------------------------

class TestQuotaOptionsFromDict:
    def test_defaults(self):
        opts = QuotaOptions.from_dict({})
        assert opts.enabled is False
        assert opts.max_runs == 10
        assert opts.window_seconds == 3600

    def test_full(self):
        opts = QuotaOptions.from_dict({"quota": {"enabled": True, "max_runs": 5, "window_seconds": 7200}})
        assert opts.enabled is True
        assert opts.max_runs == 5
        assert opts.window_seconds == 7200

    def test_enabled_coerced_to_bool(self):
        opts = QuotaOptions.from_dict({"quota": {"enabled": 1}})
        assert opts.enabled is True


# ---------------------------------------------------------------------------
# State persistence
# ---------------------------------------------------------------------------

def test_load_missing_returns_empty_state(state_dir: Path):
    opts = _opts(state_dir)
    state = load_quota_state(opts, "my-job")
    assert state.timestamps == []


def test_save_creates_file(state_dir: Path):
    opts = _opts(state_dir)
    state = QuotaState(timestamps=[1000.0, 2000.0])
    save_quota_state(opts, "my-job", state)
    path = _state_path(state_dir, "my-job")
    assert path.exists()


def test_save_and_load_roundtrip(state_dir: Path):
    opts = _opts(state_dir)
    state = QuotaState(timestamps=[1111.1, 2222.2])
    save_quota_state(opts, "my-job", state)
    loaded = load_quota_state(opts, "my-job")
    assert loaded.timestamps == pytest.approx([1111.1, 2222.2])


def test_state_path_sanitizes_slashes(state_dir: Path):
    path = _state_path(state_dir, "ns/my job")
    assert "/" not in path.name
    assert " " not in path.name


# ---------------------------------------------------------------------------
# check_quota
# ---------------------------------------------------------------------------

def test_disabled_always_allows(state_dir: Path):
    opts = QuotaOptions(enabled=False, max_runs=0, window_seconds=60, state_dir=state_dir)
    result = check_quota(opts, "job", now=1000.0)
    assert result.allowed is True


def test_first_run_allowed(state_dir: Path):
    opts = _opts(state_dir, max_runs=3)
    result = check_quota(opts, "job", now=1000.0)
    assert result.allowed is True
    assert result.run_count == 0


def test_quota_exceeded_blocks(state_dir: Path):
    opts = _opts(state_dir, max_runs=2, window=60)
    now = 1000.0
    check_quota(opts, "job", now=now)
    check_quota(opts, "job", now=now + 1)
    result = check_quota(opts, "job", now=now + 2)
    assert result.allowed is False
    assert result.run_count == 2


def test_old_timestamps_pruned(state_dir: Path):
    opts = _opts(state_dir, max_runs=2, window=60)
    old_now = 1000.0
    check_quota(opts, "job", now=old_now)          # inside window initially
    check_quota(opts, "job", now=old_now + 1)
    # advance time past window so both timestamps expire
    new_now = old_now + 120
    result = check_quota(opts, "job", now=new_now)
    assert result.allowed is True
    assert result.run_count == 0


def test_quota_result_summary_ok(state_dir: Path):
    opts = _opts(state_dir, max_runs=5)
    result = check_quota(opts, "job", now=1000.0)
    assert "OK" in result.summary()


def test_quota_result_summary_exceeded(state_dir: Path):
    opts = _opts(state_dir, max_runs=1, window=60)
    check_quota(opts, "job", now=1000.0)
    result = check_quota(opts, "job", now=1001.0)
    assert "exceeded" in result.summary()
    assert result.ok is False
