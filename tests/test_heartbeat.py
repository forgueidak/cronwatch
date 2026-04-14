"""Tests for cronwatch.heartbeat."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from cronwatch.heartbeat import (
    HeartbeatOptions,
    HeartbeatResult,
    check_heartbeat,
    record_heartbeat,
    _state_path,
)


@pytest.fixture()
def state_dir(tmp_path: Path) -> str:
    return str(tmp_path / "heartbeat")


def _opts(state_dir: str, interval: int = 3600) -> HeartbeatOptions:
    return HeartbeatOptions(enabled=True, interval_seconds=interval, state_dir=state_dir)


# --- HeartbeatOptions ---

class TestHeartbeatOptionsFromDict:
    def test_defaults(self):
        opts = HeartbeatOptions.from_dict({})
        assert opts.enabled is False
        assert opts.interval_seconds == 3600
        assert opts.state_dir == "/tmp/cronwatch/heartbeat"

    def test_full(self):
        opts = HeartbeatOptions.from_dict(
            {"enabled": True, "interval_seconds": 900, "state_dir": "/var/hb"}
        )
        assert opts.enabled is True
        assert opts.interval_seconds == 900
        assert opts.state_dir == "/var/hb"


# --- state path ---

def test_state_path_sanitizes_slashes():
    p = _state_path("/tmp", "my/job name")
    assert "/" not in p.name
    assert p.suffix == ".json"


# --- record_heartbeat ---

def test_record_creates_file(state_dir):
    opts = _opts(state_dir)
    record_heartbeat("backup", opts)
    path = _state_path(state_dir, "backup")
    assert path.exists()


def test_record_writes_valid_json(state_dir):
    opts = _opts(state_dir)
    before = time.time()
    record_heartbeat("backup", opts)
    after = time.time()
    path = _state_path(state_dir, "backup")
    data = json.loads(path.read_text())
    assert before <= data["last_seen"] <= after


# --- check_heartbeat ---

def test_check_no_prior_record_is_missed(state_dir):
    opts = _opts(state_dir, interval=60)
    result = check_heartbeat("nightly", opts)
    assert result.missed is True
    assert result.last_seen is None
    assert not result.ok


def test_check_recent_record_is_ok(state_dir):
    opts = _opts(state_dir, interval=3600)
    record_heartbeat("nightly", opts)
    result = check_heartbeat("nightly", opts)
    assert result.missed is False
    assert result.ok


def test_check_stale_record_is_missed(state_dir):
    opts = _opts(state_dir, interval=1)
    path = _state_path(state_dir, "stale")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"last_seen": time.time() - 120}))
    result = check_heartbeat("stale", opts)
    assert result.missed is True


def test_summary_no_prior_record(state_dir):
    opts = _opts(state_dir)
    result = check_heartbeat("alpha", opts)
    assert "No heartbeat" in result.summary


def test_summary_missed(state_dir):
    opts = _opts(state_dir, interval=1)
    path = _state_path(state_dir, "alpha")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"last_seen": time.time() - 300}))
    result = check_heartbeat("alpha", opts)
    assert "missed" in result.summary.lower()


def test_summary_ok(state_dir):
    opts = _opts(state_dir, interval=3600)
    record_heartbeat("alpha", opts)
    result = check_heartbeat("alpha", opts)
    assert "OK" in result.summary
