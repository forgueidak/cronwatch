"""Tests for cronwatch.debounce."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from cronwatch.debounce import (
    DebounceOptions,
    DebounceResult,
    DebounceState,
    _state_path,
    check_debounce,
    load_debounce_state,
    save_debounce_state,
)


@pytest.fixture()
def state_dir(tmp_path: Path) -> str:
    return str(tmp_path / "debounce")


def _opts(state_dir: str, enabled: bool = True, window: int = 60) -> DebounceOptions:
    return DebounceOptions(enabled=enabled, window_seconds=window, state_dir=state_dir)


# ---------------------------------------------------------------------------
# DebounceOptions.from_dict
# ---------------------------------------------------------------------------

class TestDebounceOptionsFromDict:
    def test_defaults(self):
        opts = DebounceOptions.from_dict({})
        assert opts.enabled is False
        assert opts.window_seconds == 300
        assert "debounce" in opts.state_dir

    def test_full(self):
        opts = DebounceOptions.from_dict(
            {"enabled": True, "window_seconds": 120, "state_dir": "/tmp/db"}
        )
        assert opts.enabled is True
        assert opts.window_seconds == 120
        assert opts.state_dir == "/tmp/db"


# ---------------------------------------------------------------------------
# State persistence
# ---------------------------------------------------------------------------

def test_load_missing_returns_empty_state(state_dir: str):
    s = load_debounce_state(state_dir, "myjob")
    assert s.last_notified_at is None
    assert s.suppressed_count == 0


def test_save_and_load_roundtrip(state_dir: str):
    s = DebounceState(last_notified_at=1_000_000.0, suppressed_count=3)
    save_debounce_state(state_dir, "myjob", s)
    loaded = load_debounce_state(state_dir, "myjob")
    assert loaded.last_notified_at == pytest.approx(1_000_000.0)
    assert loaded.suppressed_count == 3


def test_state_path_sanitizes_slashes(state_dir: str):
    p = _state_path(state_dir, "ns/my job")
    assert "/" not in p.name
    assert " " not in p.name


def test_save_creates_parent_directory(tmp_path: Path):
    deep = str(tmp_path / "a" / "b" / "c")
    save_debounce_state(deep, "job", DebounceState(last_notified_at=1.0))
    assert Path(deep).is_dir()


# ---------------------------------------------------------------------------
# check_debounce
# ---------------------------------------------------------------------------

def test_disabled_always_allows(state_dir: str):
    opts = _opts(state_dir, enabled=False)
    result = check_debounce(opts, "job", now=time.time())
    assert result.ok() is True
    assert result.suppressed is False


def test_first_call_always_allows(state_dir: str):
    opts = _opts(state_dir)
    result = check_debounce(opts, "job", now=1_000_000.0)
    assert result.ok() is True
    assert result.suppressed is False


def test_second_call_within_window_suppresses(state_dir: str):
    opts = _opts(state_dir, window=60)
    check_debounce(opts, "job", now=1_000_000.0)
    result = check_debounce(opts, "job", now=1_000_030.0)  # 30 s later
    assert result.suppressed is True
    assert result.ok() is False
    assert result.suppressed_count == 1


def test_call_after_window_allows(state_dir: str):
    opts = _opts(state_dir, window=60)
    check_debounce(opts, "job", now=1_000_000.0)
    result = check_debounce(opts, "job", now=1_000_061.0)  # 61 s later
    assert result.suppressed is False
    assert result.suppressed_count == 0


def test_suppressed_count_increments(state_dir: str):
    opts = _opts(state_dir, window=300)
    base = 1_000_000.0
    check_debounce(opts, "job", now=base)
    check_debounce(opts, "job", now=base + 10)
    result = check_debounce(opts, "job", now=base + 20)
    assert result.suppressed_count == 2


def test_summary_suppressed(state_dir: str):
    r = DebounceResult(suppressed=True, last_notified_at=1.0, suppressed_count=5)
    assert "suppressed" in r.summary().lower()
    assert "5" in r.summary()


def test_summary_allowed(state_dir: str):
    r = DebounceResult(suppressed=False, last_notified_at=None, suppressed_count=0)
    assert "allowed" in r.summary().lower()
