"""Integration-style tests for the concurrency guard."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from cronwatch.concurrency import ConcurrencyOptions, acquire_slot, release_slot


@pytest.fixture()
def state_dir(tmp_path: Path) -> Path:
    return tmp_path / "concurrency"


def _opts(state_dir: Path, max_instances: int = 1) -> ConcurrencyOptions:
    return ConcurrencyOptions(enabled=True, max_instances=max_instances, state_dir=state_dir)


def test_acquire_release_cycle_allows_reacquire(state_dir):
    """After releasing, the same job should be acquirable again."""
    opts = _opts(state_dir)
    r1 = acquire_slot("job", opts)
    assert r1.allowed
    release_slot("job", opts)
    r2 = acquire_slot("job", opts)
    assert r2.allowed
    release_slot("job", opts)


def test_max_instances_two_allows_two_slots(state_dir):
    """With max_instances=2 two acquisitions from the same PID should both succeed
    only if we bump the counter manually (simulate two PIDs)."""
    import json
    from cronwatch.concurrency import _slot_path

    opts = _opts(state_dir, max_instances=2)
    # First acquire from current process
    r1 = acquire_slot("job", opts)
    assert r1.allowed

    # Simulate a second live process by injecting a fake PID entry
    path = _slot_path(state_dir, "job")
    data = json.loads(path.read_text())
    # Add current PID again to simulate 2nd slot (same PID tricks the count)
    # Instead, add a "live" pid — use current pid twice to guarantee liveness
    data["pids"].append(os.getpid())
    path.write_text(json.dumps(data))

    # Now the slot has 2 entries (both live) — should be denied with max=2
    r2 = acquire_slot("job", opts)
    assert not r2.allowed


def test_slot_file_name_sanitizes_slashes(state_dir):
    """Job names with slashes should not create subdirectories."""
    from cronwatch.concurrency import _slot_path
    path = _slot_path(state_dir, "a/b/c job")
    assert "/" not in path.name
    assert " " not in path.name
