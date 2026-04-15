"""Tests for cronwatch.cooldown."""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from cronwatch.cooldown import (
    CooldownOptions,
    CooldownResult,
    _state_path,
    check_cooldown,
    load_last_run,
    save_last_run,
)


@pytest.fixture()
def state_dir(tmp_path: Path) -> str:
    return str(tmp_path / "cooldown")


def _opts(state_dir: str, enabled: bool = True, interval: int = 60) -> CooldownOptions:
    return CooldownOptions(enabled=enabled, min_interval_seconds=interval, state_dir=state_dir)


# ---------------------------------------------------------------------------
# CooldownOptions.from_dict
# ---------------------------------------------------------------------------

class TestCooldownOptionsFromDict:
    def test_defaults(self):
        opts = CooldownOptions.from_dict({})
        assert opts.enabled is False
        assert opts.min_interval_seconds == 300
        assert opts.state_dir == "/tmp/cronwatch/cooldown"

    def test_full(self):
        opts = CooldownOptions.from_dict(
            {"enabled": True, "min_interval_seconds": 120, "state_dir": "/tmp/cd"}
        )
        assert opts.enabled is True
        assert opts.min_interval_seconds == 120
        assert opts.state_dir == "/tmp/cd"


# ---------------------------------------------------------------------------
# state path
# ---------------------------------------------------------------------------

def test_state_path_sanitizes_slashes(tmp_path):
    p = _state_path(str(tmp_path), "my/job name")
    assert "/" not in p.name
    assert p.suffix == ".json"


# ---------------------------------------------------------------------------
# save / load
# ---------------------------------------------------------------------------

def test_load_missing_returns_none(state_dir):
    assert load_last_run(state_dir, "myjob") is None


def test_save_creates_file(state_dir):
    save_last_run(state_dir, "myjob")
    p = _state_path(state_dir, "myjob")
    assert p.exists()


def test_save_and_load_roundtrip(state_dir):
    ts = time.time() - 1000
    save_last_run(state_dir, "myjob", ts=ts)
    loaded = load_last_run(state_dir, "myjob")
    assert loaded == pytest.approx(ts, abs=0.01)


# ---------------------------------------------------------------------------
# check_cooldown
# ---------------------------------------------------------------------------

def test_disabled_always_allows(state_dir):
    save_last_run(state_dir, "j", ts=time.time())  # just ran
    opts = _opts(state_dir, enabled=False)
    result = check_cooldown(opts, "j")
    assert result.allowed is True


def test_no_previous_run_allows(state_dir):
    opts = _opts(state_dir)
    result = check_cooldown(opts, "new-job")
    assert result.allowed is True
    assert result.last_run_at is None


def test_run_within_interval_suppressed(state_dir):
    opts = _opts(state_dir, interval=300)
    save_last_run(state_dir, "j", ts=time.time() - 10)  # only 10s ago
    result = check_cooldown(opts, "j")
    assert result.allowed is False
    assert result.seconds_remaining > 0


def test_run_after_interval_allowed(state_dir):
    opts = _opts(state_dir, interval=30)
    save_last_run(state_dir, "j", ts=time.time() - 60)  # 60s ago > 30s interval
    result = check_cooldown(opts, "j")
    assert result.allowed is True


def test_summary_allowed():
    r = CooldownResult(allowed=True, last_run_at=None)
    assert "allowed" in r.summary()


def test_summary_suppressed():
    r = CooldownResult(allowed=False, last_run_at=time.time() - 10, seconds_remaining=50.0)
    assert "50s" in r.summary()
    assert "suppressed" in r.summary()
