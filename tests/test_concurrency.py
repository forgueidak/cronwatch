"""Tests for cronwatch.concurrency."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from cronwatch.concurrency import (
    ConcurrencyOptions,
    ConcurrencyResult,
    acquire_slot,
    release_slot,
    _slot_path,
    _live_pids,
)


@pytest.fixture()
def state_dir(tmp_path: Path) -> Path:
    return tmp_path / "concurrency"


def _opts(state_dir: Path, max_instances: int = 1, enabled: bool = True) -> ConcurrencyOptions:
    return ConcurrencyOptions(enabled=enabled, max_instances=max_instances, state_dir=state_dir)


# ---------------------------------------------------------------------------
# ConcurrencyOptions.from_dict
# ---------------------------------------------------------------------------

class TestConcurrencyOptionsFromDict:
    def test_defaults(self):
        opts = ConcurrencyOptions.from_dict({})
        assert opts.enabled is False
        assert opts.max_instances == 1

    def test_full(self, state_dir):
        opts = ConcurrencyOptions.from_dict({
            "enabled": True,
            "max_instances": 3,
            "state_dir": str(state_dir),
        })
        assert opts.enabled is True
        assert opts.max_instances == 3
        assert opts.state_dir == state_dir


# ---------------------------------------------------------------------------
# _live_pids
# ---------------------------------------------------------------------------

def test_live_pids_includes_self():
    assert os.getpid() in _live_pids([os.getpid()])


def test_live_pids_excludes_dead():
    # PID 0 is never a valid user process
    result = _live_pids([999_999_999])
    assert 999_999_999 not in result


# ---------------------------------------------------------------------------
# acquire_slot / release_slot
# ---------------------------------------------------------------------------

def test_acquire_disabled_always_allows(state_dir):
    opts = _opts(state_dir, enabled=False)
    result = acquire_slot("myjob", opts)
    assert result.allowed is True
    assert not state_dir.exists()  # no file written


def test_acquire_creates_slot_file(state_dir):
    opts = _opts(state_dir)
    result = acquire_slot("myjob", opts)
    assert result.allowed is True
    path = _slot_path(state_dir, "myjob")
    assert path.exists()
    data = json.loads(path.read_text())
    assert os.getpid() in data["pids"]


def test_acquire_denied_when_max_reached(state_dir):
    """Simulate another live PID already holding the slot."""
    opts = _opts(state_dir, max_instances=1)
    path = _slot_path(state_dir, "myjob")
    state_dir.mkdir(parents=True, exist_ok=True)
    # Write current PID as an existing holder so slot is full
    path.write_text(json.dumps({"pids": [os.getpid()]}))
    # acquire again from the same process — slot is full (1/1)
    result = acquire_slot("myjob", opts)
    assert result.allowed is False
    assert "max_instances" in result.reason


def test_acquire_allows_when_dead_pids_present(state_dir):
    """Dead PIDs should be pruned; slot should become available."""
    opts = _opts(state_dir, max_instances=1)
    path = _slot_path(state_dir, "myjob")
    state_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"pids": [999_999_999]}))
    result = acquire_slot("myjob", opts)
    assert result.allowed is True


def test_release_removes_pid(state_dir):
    opts = _opts(state_dir)
    acquire_slot("myjob", opts)
    release_slot("myjob", opts)
    path = _slot_path(state_dir, "myjob")
    data = json.loads(path.read_text())
    assert os.getpid() not in data["pids"]


def test_release_disabled_is_noop(state_dir):
    opts = _opts(state_dir, enabled=False)
    release_slot("myjob", opts)  # must not raise


def test_concurrency_result_summary_ok():
    r = ConcurrencyResult(allowed=True, active_pids=[1, 2])
    assert "ok" in r.summary()
    assert r.ok is True


def test_concurrency_result_summary_denied():
    r = ConcurrencyResult(allowed=False, reason="max_instances=1 reached")
    assert "denied" in r.summary()
    assert r.ok is False
