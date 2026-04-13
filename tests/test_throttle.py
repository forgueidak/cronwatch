"""Tests for cronwatch.throttle."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from cronwatch.throttle import (
    ThrottleOptions,
    ThrottleState,
    _state_path,
    clear_throttle_state,
    is_throttled,
    load_throttle_state,
    record_alert,
    save_throttle_state,
)


@pytest.fixture()
def state_dir(tmp_path: Path) -> str:
    return str(tmp_path / "throttle")


def _opts(state_dir: str, cooldown: int = 3600) -> ThrottleOptions:
    return ThrottleOptions(cooldown_seconds=cooldown, state_dir=state_dir)


# ---------------------------------------------------------------------------
# load / save / clear
# ---------------------------------------------------------------------------

def test_load_throttle_state_missing(state_dir: str) -> None:
    assert load_throttle_state("my-job", state_dir) is None


def test_save_creates_file(state_dir: str) -> None:
    save_throttle_state("my-job", state_dir)
    path = _state_path("my-job", state_dir)
    assert path.exists()


def test_save_and_load_roundtrip(state_dir: str) -> None:
    before = time.time()
    save_throttle_state("backup", state_dir)
    state = load_throttle_state("backup", state_dir)
    assert state is not None
    assert state.job_name == "backup"
    assert state.last_alerted_at >= before


def test_clear_removes_file(state_dir: str) -> None:
    save_throttle_state("my-job", state_dir)
    clear_throttle_state("my-job", state_dir)
    assert load_throttle_state("my-job", state_dir) is None


def test_clear_missing_file_is_noop(state_dir: str) -> None:
    clear_throttle_state("nonexistent", state_dir)  # should not raise


def test_load_corrupt_file_returns_none(state_dir: str) -> None:
    path = _state_path("bad", state_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{invalid json")
    assert load_throttle_state("bad", state_dir) is None


# ---------------------------------------------------------------------------
# is_throttled / record_alert
# ---------------------------------------------------------------------------

def test_is_throttled_no_state(state_dir: str) -> None:
    opts = _opts(state_dir)
    assert is_throttled("fresh-job", opts) is False


def test_is_throttled_within_cooldown(state_dir: str) -> None:
    opts = _opts(state_dir, cooldown=3600)
    record_alert("my-job", opts)
    assert is_throttled("my-job", opts) is True


def test_is_throttled_expired_cooldown(state_dir: str) -> None:
    opts = _opts(state_dir, cooldown=1)
    record_alert("my-job", opts)
    # Manually backdate the state
    path = _state_path("my-job", state_dir)
    data = json.loads(path.read_text())
    data["last_alerted_at"] = time.time() - 10
    path.write_text(json.dumps(data))
    assert is_throttled("my-job", opts) is False


def test_record_alert_returns_state(state_dir: str) -> None:
    opts = _opts(state_dir)
    state = record_alert("deploy", opts)
    assert isinstance(state, ThrottleState)
    assert state.job_name == "deploy"


def test_job_name_with_slashes(state_dir: str) -> None:
    opts = _opts(state_dir)
    record_alert("/etc/cron.d/backup", opts)
    assert is_throttled("/etc/cron.d/backup", opts) is True
